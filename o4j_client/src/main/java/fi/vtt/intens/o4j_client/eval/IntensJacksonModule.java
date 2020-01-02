package fi.vtt.intens.o4j_client.eval;

import com.fasterxml.jackson.core.json.JsonReadFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.json.JsonMapper;
import com.fasterxml.jackson.dataformat.yaml.YAMLMapper;
import com.fasterxml.jackson.datatype.jsonorg.JsonOrgModule;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.google.inject.AbstractModule;
import com.google.inject.Provides;
import com.google.inject.Singleton;
import com.google.inject.name.Named;

/**
 * Bindings for reading YAML and JSON with Jackson.
 */
public class IntensJacksonModule extends AbstractModule {
    @Provides
    @Named("intensModel")
    @Singleton
    public static ObjectMapper getModelOM() {
        return YAMLMapper.builder()
                .addModule(new JavaTimeModule())
                .build();
    }

    @Provides
    @Named("intensProtocol")
    @Singleton
    public static ObjectMapper getProtocolOM() {
        return JsonMapper.builder()
                .addModule(new JsonOrgModule())
                .enable(JsonReadFeature.ALLOW_NON_NUMERIC_NUMBERS)
                .build();
    }
}
