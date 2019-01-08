package fi.vtt.intens.o4j_client.eval;

import java.io.IOException;

import com.fasterxml.jackson.annotation.JsonTypeName;

import okhttp3.Authenticator;
import okhttp3.Credentials;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.Route;

/**
 * Implements HTTP basic authentication for OkHttp3.
 * Based on an example in the library documentation.
 */
@JsonTypeName("BasicAuth")
public class BasicAuthenticator implements Authenticator {
    public String username, password;

    public BasicAuthenticator() {}

    public BasicAuthenticator(String username, String password) {
        this.username = username;
        this.password = password;
    }

    @Override
    public Request authenticate(Route route, Response response)
            throws IOException {
        var req = response.request();
        if (req.header("Authorization") != null)
            // Tried that, didn't work.
            return null;
        else
            return req.newBuilder().header(
                    "Authorization", Credentials.basic(username, password))
                    .build();
    }
}
