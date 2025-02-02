# -*- coding: utf-8 -*-

import logging
import timeit
import typing

from flask import Blueprint, make_response, jsonify, current_app, g
from flask_restplus import fields

from gordo_components import __version__
from gordo_components.server.rest_api import Api
from gordo_components.server.views.base import BaseModelView
from gordo_components.server import utils


logger = logging.getLogger(__name__)

anomaly_blueprint = Blueprint("ioc_anomaly_blueprint", __name__, url_prefix="/anomaly")

api = Api(
    app=anomaly_blueprint,
    title="Gordo API IOC Anomaly Docs",
    version=__version__,
    description="Documentation for the Gordo ML Server",
    default_label="Gordo Endpoints",
)

# POST type declarations
API_MODEL_INPUT_POST = api.model(
    "Prediction - Multiple Samples", {"X": fields.List(fields.List(fields.Float))}
)
API_MODEL_OUTPUT_POST = api.model(
    "Prediction - Output from POST", {"output": fields.List(fields.List(fields.Float))}
)


# GET type declarations
API_MODEL_INPUT_GET = api.model(
    "Prediction - Time range prediction",
    {"start": fields.DateTime, "end": fields.DateTime},
)
_tags = {
    fields.String: fields.Float
}  # tags of single prediction record {'tag-name': tag-value}
_single_prediction_record = {
    "start": fields.DateTime,
    "end": fields.DateTime,
    "tags": fields.Nested(_tags),
    "total_abnormality": fields.Float,
}
API_MODEL_OUTPUT_GET = api.model(
    "Prediction - Output from GET",
    {"output": fields.List(fields.Nested(_single_prediction_record))},
)


class AnomalyView(BaseModelView):
    """
    Serve model predictions via GET and POST methods

    Will take a ``start`` and ``end`` ISO format datetime string if a GET request
    or will take the raw input given in a POST request
    and give back predictions looking something like this
    (depending on anomaly model being served)::

        {
        'data': [
            {
           'end': ['2016-01-01T00:10:00+00:00'],
           'tag-anomaly': [0.913027075986948,
                         0.3474043585419292,
                         0.8986610906818544,
                         0.11825221990818557],
           'model-output': [0.0005317790200933814,
                            -0.0001525811239844188,
                            0.0008310950361192226,
                            0.0015755111817270517],
           'original-input': [0.9135588550070414,
                              0.3472517774179448,
                              0.8994921857179736,
                              0.11982773108991263],
           'start': ['2016-01-01T00:00:00+00:00'],
           'total-anomaly': [1.3326228173185086],
            },
            ...
        ],

     'tags': [{'asset': None, 'name': 'tag-0'},
              {'asset': None, 'name': 'tag-1'},
              {'asset': None, 'name': 'tag-2'},
              {'asset': None, 'name': 'tag-3'}],
     'time-seconds': '0.1937'}
    """

    @api.response(200, "Success", API_MODEL_OUTPUT_POST)
    @api.expect(API_MODEL_INPUT_POST, validate=False)
    @api.doc(
        params={
            "X": "Nested list of samples to predict, or single list considered as one sample"
        }
    )
    @utils.extract_X_y
    def post(self):
        start_time = timeit.default_timer()
        return self._create_anomaly_response(start_time)

    @api.response(200, "Success", API_MODEL_OUTPUT_POST)
    @api.doc(
        params={
            "start": "An ISO formatted datetime with timezone info string indicating prediction range start",
            "end": "An ISO formatted datetime with timezone info string indicating prediction range end",
        }
    )
    @utils.extract_X_y
    def get(self):
        start_time = timeit.default_timer()
        return self._create_anomaly_response(start_time)

    def _create_anomaly_response(self, start_time: float = None):
        """
        Process a base response from POST or GET endpoints, where it is expected in
        the anomaly endpoint that the keys "output", "transformed-model-input" and "inverse-transformed-output"
        are expected to be present in ``.json`` of the Response.

        Parameters
        ----------
        start_time: Optional[float]
            Start time to use when timing the processing time of the request, will construct a new
            one if not provided.

        Returns
        -------
        flask.Response
            The formatted anomaly representation response object.
        """
        if start_time is None:
            start_time = timeit.default_timer()

        # To use this endpoint, we need a 'y' to calculate the errors.
        # It has either come from client providing it in POST or from
        # Influx during 'GET' part of `..common.extract_X_y` decorator
        if g.y is None:
            message = {
                "message": "Cannot perform anomaly without 'y' to compare against."
            }
            return make_response((jsonify(message), 400))

        # It is ok for y to be a subset of features in X, but we need at least one
        # to compare against to calculate an error.
        if not any(col in g.y.columns for col in [t.name for t in self.tags]):
            message = {"message": "y is not a subset of X, cannot do anomaly detection"}
            return make_response(jsonify(message), 400)

        # Now create an anomaly dataframe from the base response dataframe
        try:
            anomaly_df = current_app.model.anomaly(g.X, g.y, frequency=self.frequency)
        except AttributeError:
            msg = {
                "message": f"Model is not an AnomalyDetector, it is of type: {type(current_app.model)}"
            }
            return make_response(jsonify(msg), 422)  # 422 Unprocessable Entity

        context: typing.Dict[typing.Any, typing.Any] = dict()
        context["data"] = utils.multi_lvl_column_dataframe_to_dict(anomaly_df)
        context["time-seconds"] = f"{timeit.default_timer() - start_time:.4f}"
        return make_response(jsonify(context), context.pop("status-code", 200))


api.add_resource(AnomalyView, "/prediction")
