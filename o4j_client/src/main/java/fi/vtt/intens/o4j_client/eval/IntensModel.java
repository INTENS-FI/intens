package fi.vtt.intens.o4j_client.eval;

import java.io.IOException;
import java.io.Writer;
import java.net.URI;
import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Locale.LanguageRange;
import java.util.Map;

import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonInclude.Include;
import com.fasterxml.jackson.annotation.JsonProperty;

import eu.cityopt.sim.eval.Namespace;
import eu.cityopt.sim.eval.SimulationInput;
import eu.cityopt.sim.eval.SimulationModel;

/**
 * A reference to a pre-deployed simsvc instance.
 * This is intended to be read from YAML with Jackson.
 * An url is required, most other parameters are optional. 
 */
@JsonInclude(Include.NON_ABSENT)
public class IntensModel implements SimulationModel {
    @JsonProperty("url")
    public URI uri;
    public Map<Locale, String> descriptions = new HashMap<>();
    public String simulatorName;
    public String logFile;
    public Defaults defaults = new Defaults();
    public Duration nominalSimulationRuntime;

    IntensManager simulationManager;

    public void close() throws IOException {}

    @JsonIgnore
    public IntensManager getSimulatorManager() {
        return simulationManager;
    }

    public String getSimulatorName() {
        return simulatorName;
    }

    public Defaults getDefaults() {
        return defaults;
    }

    public Duration getNominalSimulationRuntime() {
        return nominalSimulationRuntime;
    }

    @JsonIgnore
    public String getDescription(List<LanguageRange> priorityList) {
        Locale loc = Locale.lookup(priorityList, descriptions.keySet());
        return (loc != null) ? descriptions.get(loc) : null;
    }

    @JsonIgnore
    public byte[] getOverviewImageData() {
        // TODO Auto-generated method stub
        return null;
    }

    public SimulationInput findInputsAndOutputs(
            Namespace newNamespace, Map<String, Map<String, String>> units,
            int detailLevel, Writer warningWriter) throws IOException {
        // TODO Auto-generated method stub
        return null;
    }

}
