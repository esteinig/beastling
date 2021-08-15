from pydantic import BaseModel, ValidationError, root_validator
from critter.blocks.distributions import Distribution
from critter.blocks.parameters import RealParameter
from critter.utils import get_uuid
from critter.errors import CritterError
from math import inf as infinity
from typing import List


class Prior(BaseModel):
    """ Base class for priors """
    id: str = f'Prior.{get_uuid(short=True)}'  # prior identifier prefix defined in all prior subclasses (id="")

    distribution: List[Distribution]  # prior distribution/s, configured
    initial: List
    lower: float = -infinity
    upper: float = infinity
    dimension: int = 1
    sliced: bool = False
    intervals: list = []
    param_spec: str = "parameter.RealParameter"  # changes in MTDB model to IntegerParameter

    def __str__(self):
        return self.xml

    @property
    def xml(self) -> str:
        if not self.sliced:
            # Normal singular prior distribution
            return f'<prior id="{self.id}Prior" name="distribution" ' \
                   f'x="@{self.id}">{self.distribution[0].xml}</prior>'
        else:
            # Sliced sampling proportion distribution per interval
            sliced_priors = ''
            for i, distribution in enumerate(self.distribution):
                sliced_priors += f'<prior id="{self.id}Slice{i+1}" name="distribution" ' \
                                 f'x="@{self.id}{i+1}">{distribution.xml}</prior>'
            return sliced_priors

    @property  # alias
    def xml_prior(self) -> str:
        return self.xml

    @property
    def xml_param(self) -> str:
        # Allow for higher dimensions using slices
        initial = " ".join(str(i) for i in self.initial) if len(self.initial) > 1 else self.initial[0]
        param = RealParameter(  # TODO: validators on RealParameter
            id=f"{self.id}", name="stateNode", value=initial, spec=self.param_spec,
            dimension=self.dimension, lower=self.lower, upper=self.upper
        )
        return param.xml

    @property
    def xml_logger(self) -> str:
        return f'<log idref="{self.id}"/>'

    # Clock scale operator for priors
    @property
    def xml_scale_operator(self):
        return

    # Sliced priors: slice function, rate change times, and logger
    @property
    def xml_slice_function(self) -> str:
        if not self.sliced:
            return ''
        else:
            xml = ''
            for i, _ in enumerate(self.distribution):
                xml += f'<function spec="beast.core.util.Slice" id="{self.id}{i+1}" ' \
                    f'arg="@{self.id}" index="{i}" count="1"/>\n'
            return xml

    @property
    def xml_slice_rate_change_times(self) -> str:
        if not self.sliced:
            return ''
        else:
            intervals = " ".join(str(i) for i in self.intervals)
            if self.id.startswith('samplingProportion'):
                rate_change_times = 'samplingRateChangeTimes'
            elif self.id.startswith('rho'):
                rate_change_times = 'samplingRateChangeTimes'
            elif self.id.startswith('reproductiveNumber'):
                rate_change_times = 'birthRateChangeTimes'
            elif self.id.startswith('becomeUninfectious'):
                rate_change_times = 'deathRateChangeTimes'
            else:
                raise CritterError(
                    'Rate change times (slices or intervals) are only defined for: '
                    'rho and samplingProportion (<samplingRateChangeTimes/>), '
                    'reproductiveNumber (<birthRateChangeTimes/>) and'
                    'becomeUninfectious (<deathRateChangeTime/>) priors'
                )

            return f'<{rate_change_times} spec="beast.core.parameter.RealParameter" value="{intervals}"/>'

    @property
    def xml_slice_logger(self) -> str:
        if not self.sliced:
            return ''
        else:
            loggers = ''
            for i, value in enumerate(self.distribution):
                loggers += f'<log idref="{self.id}{i+1}"/>\n'
            return loggers

    @root_validator
    def validate_sliced_id(cls, fields):
        # Slicing only available for a subset of priors (BDSky models)
        if fields.get('sliced') and not fields.get('id').startswith(
            ('origin', 'rho', 'samplingProportion', 'reproductiveNumber', 'becomeUninfectious')
        ):
            raise ValidationError(
                'Cannot create a sliced prior that does not belong to a valid birth-death model prior. '
                'Sliced prior model identifier fields must start with one of: '
                'origin, rho, samplingProportion, reproductiveNumber, becomeUninfectious'
            )
        else:
            return fields


# Birth-Death Skyline Serial
class Origin(Prior):
    id = "origin"


class ReproductiveNumber(Prior):
    id = "reproductiveNumber"


class SamplingProportion(Prior):
    id = "samplingProportion"


class BecomeUninfectiousRate(Prior):
    id = "becomeUninfectiousRate"


class Rho(Prior):
    id = "rho"


# MultiType BirthDeath Priors /w modifications to SamplingProportion
class RateMatrix(Prior):
    id = "rateMatrix"


class SamplingProportionMTBD(Prior):
    id = "samplingProportion"

    # Using a distribution component for prior here, not sure why:
    @property
    def xml(self) -> str:
        return f'<distribution id="{self.id}Prior" ' \
               f'spec="multitypetree.distributions.ExcludablePrior" x="@{self.id}">' \
               f'<xInclude id="samplingProportionXInclude" spec="parameter.BooleanParameter" dimension="{self.dimension}">' \
               f'{self.get_include_string()}</xInclude>{self.distribution[0].xml}</distribution>'

    def get_include_string(self) -> str:
        incl = ['true' if v != 0 else 'false' for v in self.initial]
        return ' '.join(incl)


# Coalescent Bayesian Skyline
class PopulationSize(Prior):
    id = 'bPopSizes'


class GroupSize(Prior):
    id = 'bGroupSizes'
    param_spec = 'parameter.IntegerParameter'

    @property
    def state_node_group_size(self) -> str:
        return f'<stateNode id="bGroupSizes" spec="parameter.IntegerParameter" ' \
            f'dimension="{self.dimension}">{self.initial}</stateNode>'


# Clock priors
class ClockRate(Prior):
    id = 'clockRate'


class UCRE(Prior):
    id = 'ucreMean'


class UCRLMean(Prior):
    id = 'ucrlMean'


class UCRLSD(Prior):
    id = 'ucrlSD'
