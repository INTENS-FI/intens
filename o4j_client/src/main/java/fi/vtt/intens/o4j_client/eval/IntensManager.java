package fi.vtt.intens.o4j_client.eval;

import java.io.IOException;
import java.io.InputStream;

import javax.inject.Inject;
import javax.inject.Named;

import com.fasterxml.jackson.core.JsonParseException;
import com.fasterxml.jackson.databind.JsonMappingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.dataformat.yaml.JacksonYAMLParseException;

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
    public ObjectMapper om;

    @Inject
    public IntensManager(@Named("intensModel") ObjectMapper om) {
        this.om = om;
    }

    public void close() throws IOException {}

    public IntensModel parseModel(String simulatorName, InputStream modelData)
            throws IOException, ConfigurationException {
        try {
            IntensModel model = om.readValue(modelData, IntensModel.class);
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

    public IntensRunner makeRunner(SimulationModel model, Namespace namespace)
            throws IOException, ConfigurationException {
        IntensModel intModel = (IntensModel)model;
        // TODO Auto-generated method stub
        return null;
    }

}
