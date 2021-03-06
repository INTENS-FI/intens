package fi.vtt.intens.o4j_client.eval;

import java.io.IOException;
import java.io.Writer;
import java.net.URI;
import java.nio.file.Path;
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
import com.fasterxml.jackson.annotation.JsonSubTypes;
import com.fasterxml.jackson.annotation.JsonSubTypes.Type;
import com.fasterxml.jackson.annotation.JsonTypeInfo;

import eu.cityopt.sim.eval.Namespace;
import eu.cityopt.sim.eval.SimulationInput;
import eu.cityopt.sim.eval.SimulationModel;
import okhttp3.Authenticator;

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
    public Path cafile;
    @JsonTypeInfo(use=JsonTypeInfo.Id.NAME,
                  defaultImpl=BasicAuthenticator.class)
    @JsonSubTypes({@Type(BasicAuthenticator.class)})
    public Authenticator auth;

    IntensManager simulationManager;

    @Override
    public void close() throws IOException {}

    @Override
    @JsonIgnore
    public IntensManager getSimulatorManager() {
        return simulationManager;
    }

    @Override
    public String getSimulatorName() {
        return simulatorName;
    }

    @Override
    public Defaults getDefaults() {
        return defaults;
    }

    @Override
    public Duration getNominalSimulationRuntime() {
        return nominalSimulationRuntime;
    }

    @Override
    @JsonIgnore
    public String getDescription(List<LanguageRange> priorityList) {
        Locale loc = Locale.lookup(priorityList, descriptions.keySet());
        return (loc != null) ? descriptions.get(loc) : null;
    }

    @Override
    @JsonIgnore
    public byte[] getOverviewImageData() {
        return null;
    }

    @Override
    public SimulationInput findInputsAndOutputs(
            Namespace newNamespace, Map<String, Map<String, String>> units,
            int detailLevel, Writer warningWriter) throws IOException {
        // TODO Auto-generated method stub
        return null;
    }

}
