package fi.vtt.intens.o4j_client.eval;

import java.io.IOException;
import java.io.InputStream;

import javax.inject.Inject;
import javax.inject.Named;

import com.fasterxml.jackson.core.JsonParseException;
import com.fasterxml.jackson.databind.JsonMappingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsonorg.JsonOrgModule;

import eu.cityopt.sim.eval.AlienModelException;
import eu.cityopt.sim.eval.ConfigurationException;
import eu.cityopt.sim.eval.Namespace;
import eu.cityopt.sim.eval.SimulationModel;
import eu.cityopt.sim.eval.SimulatorManager;


/**
 * A factory for simulations that execute on simsvc.
 * @author ttekth
 *
 */
public class IntensManager implements SimulatorManager {

    /**
     * The {@link ObjectMapper} used by {@link #parseModel}.
     * Normally this reads YAML but I suppose one could also put
     * in a JSON mapper or even XML. 
     */
    public ObjectMapper modelOM;
    
    /**
     * The {@link ObjectMapper} used by {@link IntensRunner}s for talking
     * to the server.  It needs to have {@link JsonOrgModule}.
     */
    public ObjectMapper protocolOM;

    @Inject
    public IntensManager(@Named("intensModel") ObjectMapper modelOM,
                         @Named("intensProtocol") ObjectMapper protocolOM) {
        this.modelOM = modelOM;
        this.protocolOM = protocolOM;
    }

    @Override
    public void close() throws IOException {}

    @Override
    public IntensModel parseModel(String simulatorName, InputStream modelData)
            throws IOException, ConfigurationException {
        try {
            IntensModel model = modelOM.readValue(
                    modelData, IntensModel.class);
            model.simulationManager = this;
            return model;
        } catch (JsonParseException | JsonMappingException e) {
            String msg = "Failed to parse as IntensModel";
            if (simulatorName == null) {
                throw new AlienModelException(msg, e);
            } else {
                throw new ConfigurationException(msg, e);
            }
        }
    }

    @Override
    public IntensRunner makeRunner(SimulationModel model, Namespace namespace)
            throws IOException, ConfigurationException {
        return new IntensRunner((IntensModel)model);
    }
}
