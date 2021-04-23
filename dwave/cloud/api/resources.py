# Copyright 2021 D-Wave Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import List, Union, Optional

from dwave.cloud.api.client import SAPIClient
from dwave.cloud.api import constants, models

__all__ = ['Solvers', 'Problems']


class Resource:
    """A class for interacting with a SAPI resource."""

    resource_path = ''

    def __init__(self, **config):
        self.client = SAPIClient(**config)

        session = self.client.session
        if self.resource_path:
            # append resource_path
            session.base_url = session.create_url(self.resource_path)
        self.session = session

    @classmethod
    def from_client_config(cls, client: Union[SAPIClient, 'dwave.cloud.client.base.Client']):
        """Create Resource instance configured from a
        :class:`~dwave.cloud.client.base.Client' instance.
        """
        if isinstance(client, SAPIClient):
            return cls(**client.config)
        else: # assume isinstance(client, dwave.cloud.Client), without importing
            sapiclient = SAPIClient.from_client_config(client)
            return cls(**sapiclient.config)


class Solvers(Resource):

    resource_path = 'solvers/'

    # Content-Type: application/vnd.dwave.sapi.solver-definition-list+json; version=2.0.0
    def list_solvers(self) -> List[models.SolverConfiguration]:
        path = 'remote/'
        response = self.session.get(path)
        solvers = response.json()
        return [models.SolverConfiguration(**s) for s in solvers]

    # Content-Type: application/vnd.dwave.sapi.solver-definition+json; version=2.0.0
    def get_solver(self, solver_id: str) -> models.SolverConfiguration:
        path = 'remote/{}'.format(solver_id)
        response = self.session.get(path)
        solver = response.json()
        return models.SolverConfiguration(**solver)


class Problems(Resource):

    resource_path = 'problems/'

    # Content-Type: application/vnd.dwave.sapi.problems+json; version=2.1.0
    def list_problems(self, **params) -> List[models.ProblemStatus]:
        # available params: id, label, max_results, status, solver
        path = ''
        response = self.session.get(path, params=params)
        statuses = response.json()
        return [models.ProblemStatus(**s) for s in statuses]

    # Content-Type: application/vnd.dwave.sapi.problem+json; version=2.1.0
    def get_problem(self, problem_id: str) -> models.ProblemStatusMaybeWithAnswer:
        """Retrieve problem short status and answer if answer is available."""
        path = '{}'.format(problem_id)
        response = self.session.get(path)
        status = response.json()
        return models.ProblemStatusMaybeWithAnswer(**status)

    # Content-Type: application/vnd.dwave.sapi.problems+json; version=2.1.0
    def get_problem_status(self, problem_id: str) -> models.ProblemStatus:
        """Retrieve short status of a single problem."""
        path = ''
        params = dict(id=problem_id)
        response = self.session.get(path, params=params)
        status = response.json()[0]
        return models.ProblemStatus(**status)

    # Content-Type: application/vnd.dwave.sapi.problems+json; version=2.1.0
    def get_problem_statuses(self, problem_ids: List[str]) -> List[models.ProblemStatus]:
        """Retrieve short problem statuses for a list of problems."""
        if len(problem_ids) > 1000:
            raise ValueError('number of problem ids is limited to 1000')

        path = ''
        params = dict(id=','.join(problem_ids))
        response = self.session.get(path, params=params)
        statuses = response.json()
        return [models.ProblemStatus(**s) for s in statuses]

    # Content-Type: application/vnd.dwave.sapi.problem-data+json; version=2.1.0
    def get_problem_info(self, problem_id: str) -> models.ProblemInfo:
        """Retrieve complete problem info."""
        path = '{}/info'.format(problem_id)
        response = self.session.get(path)
        info = response.json()
        return models.ProblemInfo(**info)

    # Content-Type: application/vnd.dwave.sapi.problem-answer+json; version=2.1.0
    def get_problem_answer(self, problem_id: str) -> models.ProblemAnswer:
        """Retrieve problem answer."""
        path = '{}/answer'.format(problem_id)
        response = self.session.get(path)
        answer = response.json()['answer']
        return models.ProblemAnswer(**answer)

    # Content-Type: application/vnd.dwave.sapi.problem-message+json; version=2.1.0
    def get_problem_messages(self, problem_id: str) -> List[dict]:
        """Retrieve list of problem messages."""
        path = '{}/messages'.format(problem_id)
        response = self.session.get(path)
        return response.json()

    # Content-Type: application/vnd.dwave.sapi.problems+json; version=2.1.0
    def submit_problem(self,
                       data: models.ProblemData,
                       params: dict,
                       solver: str,
                       type: constants.ProblemType,
                       label: str = None) -> models.ProblemStatusMaybeWithAnswer:
        """Blocking problem submit with timeout, returning final status and
        answer, if problem was solved within the (undisclosed) time limit.
        """
        path = ''
        body = dict(data=data.dict(), params=params, solver=solver,
                    type=type, label=label)
        response = self.session.post(path, json=body)
        return models.ProblemStatusMaybeWithAnswer(**response.json())

    # Content-Type: application/vnd.dwave.sapi.problems+json; version=2.1.0
    def submit_problems(self, problems: List[models.ProblemJob]) -> \
            List[Union[models.ProblemInitialStatus, models.ProblemSubmitError]]:
        """Asynchronous multi-problem submit, returning initial statuses."""
        path = ''
        # encode piecewise so that enums are serialized (via pydantic encoder)
        body = '[%s]' % ','.join(p.json() for p in problems)
        response = self.session.post(path, data=body,
                                     headers={'Content-Type': 'application/json'})
        statuses = response.json()
        return [models.ProblemInitialStatus(**s) if 'status' in s
                else models.ProblemSubmitError(**s)
                for s in statuses]

    # Content-Type: application/vnd.dwave.sapi.problem+json; version=2.1.0
    def cancel_problem(self, problem_id: str) -> models.ProblemStatus:
        """Initiate problem cancel by problem id."""
        path = '{}/'.format(problem_id)
        response = self.session.delete(path)
        status = response.json()
        return models.ProblemStatus(**status)

    # Content-Type: application/vnd.dwave.sapi.problems+json; version=2.1.0
    def cancel_problems(self, problem_ids: List[str]) -> \
            List[Union[models.ProblemStatus, models.ProblemCancelError]]:
        """Initiate problem cancel for a list of problems."""
        path = ''
        response = self.session.delete(path, json=problem_ids)
        statuses = response.json()
        return [models.ProblemStatus(**s) if 'status' in s
                else models.ProblemCancelError(**s)
                for s in statuses]
