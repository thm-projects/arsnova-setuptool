package de.thm.arsnova.setuptool;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.util.Map;

import org.apache.http.HttpResponse;
import org.apache.http.client.HttpClient;
import org.apache.http.client.methods.HttpDelete;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.client.methods.HttpPut;
import org.apache.http.entity.ContentType;
import org.apache.http.entity.StringEntity;
import org.apache.http.impl.client.DefaultHttpClient;
import org.apache.http.util.EntityUtils;
import org.codehaus.jackson.map.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.ApplicationContext;
import org.springframework.context.support.ClassPathXmlApplicationContext;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

@Component
public class Application {

	private String databaseHost;
	private String databasePort;
	private String databaseName;
	private String databaseUser;
	private String databasePasswd;

	private final HttpClient httpClient = new DefaultHttpClient();

	@Value("${couchdb.host}")
	public final void setDatabaseHost(String databaseHost) {
		this.databaseHost = databaseHost;
	}

	@Value("${couchdb.port}")
	public final void setDatabasePort(String databasePort) {
		this.databasePort = databasePort;
	}

	@Value("${couchdb.name}")
	public final void setDatabaseName(String databaseName) {
		this.databaseName = databaseName;
	}

	@Value("${couchdb.username}")
	public final void setDatabaseUsername(String databaseUser) {
		this.databaseUser = databaseUser;
	}

	@Value("${couchdb.password}")
	public final void setDatabasePasswd(String databasePasswd) {
		this.databasePasswd = databasePasswd;
	}

	public static void main(String[] args) throws IOException {
		ApplicationContext context = new ClassPathXmlApplicationContext(
				"application-context.xml");
		Application app = context.getBean(Application.class);

		app.startup();
	}

	public void startup() {
		// Create Database if not exists
		if (this.createDatabase()) {
			System.out.println("Database exists or has been created");
		}

		try {
			File viewDirectory = new ClassPathResource("views").getFile();
			if (viewDirectory.isDirectory()) {
				for (File viewFile : viewDirectory.listFiles()) {
					BufferedReader reader = new BufferedReader(new FileReader(
							viewFile));

					StringBuilder sb = new StringBuilder();
					String line;
					while ((line = reader.readLine()) != null) {
						sb.append(line);
					}
					reader.close();

					this.setupView(viewFile.getName(), sb.toString());
				}
			}
		} catch (Exception e) {
			System.out.println("An error occured on view setup process");
		}
	}

	private void setupView(String documentName, String viewCode) {
		if (documentExists(documentName)) {
			deleteDocument(documentName);
			createDocument(documentName, viewCode);
			System.out.println("View '" + documentName + "' has been updated");
			return;
		}

		if (createDocument(documentName, viewCode))
			System.out.println("View '" + documentName + "' has been created");
	}

	private String getDocumentUri(String documentName) {
		return this.getDatabaseUri() + "/_document/" + documentName;
	}

	private boolean documentExists(String documentName) {
		try {
			HttpGet get = new HttpGet(this.getDocumentUri(documentName));
			HttpResponse response = httpClient.execute(get);
			EntityUtils.consume(response.getEntity());
			if (response.getStatusLine().getStatusCode() == 200)
				return true;
		} catch (Exception e) {
			e.printStackTrace();
			return false;
		}

		return false;
	}

	private String documentRev(String documentName) {
		try {
			HttpGet get = new HttpGet(this.getDocumentUri(documentName));
			HttpResponse getResponse = httpClient.execute(get);
			String document = EntityUtils.toString(getResponse.getEntity());
			EntityUtils.consume(getResponse.getEntity());
			ObjectMapper mapper = new ObjectMapper();
			@SuppressWarnings("unchecked")
			Map<String,Object> documentData = mapper.readValue(document, Map.class);
			return documentData.get("_rev").toString();
		} catch (Exception e) {
		}
		return null;
	}

	private boolean deleteDocument(String documentName) {
		try {
			HttpDelete delete = new HttpDelete(
					this.getDocumentUri(documentName) + "?rev=" + documentRev(documentName));
			HttpResponse response = httpClient.execute(delete);
			EntityUtils.consume(response.getEntity());
			System.out.println(response.getStatusLine().getStatusCode());
			if (response.getStatusLine().getStatusCode() == 204)
				return true;
		} catch (Exception e) {
			e.printStackTrace();
			return false;
		}

		return false;
	}

	private boolean createDocument(String documentName, String contents) {
		try {
			HttpPost post = new HttpPost(this.getDatabaseUri());
			StringEntity entity = new StringEntity(contents,
					ContentType.create("application/json", "UTF-8"));
			post.setEntity(entity);
			HttpResponse response = httpClient.execute(post);
			System.out.println(EntityUtils.toString(response.getEntity()));
			System.out.println("X" + response.getStatusLine().getStatusCode());
			EntityUtils.consume(response.getEntity());
			if (response.getStatusLine().getStatusCode() == 201)
				return true;
		} catch (Exception e) {
			e.printStackTrace();
			return false;
		}

		return false;
	}

	private String getDatabaseUri() {
		return "http://" + databaseUser + ":" + databasePasswd + "@"
				+ databaseHost + ":" + databasePort + "/" + databaseName;
	}

	private boolean databaseExists() {
		try {
			HttpGet get = new HttpGet(this.getDatabaseUri());
			HttpResponse response = httpClient.execute(get);
			EntityUtils.consume(response.getEntity());
			if (response.getStatusLine().getStatusCode() == 200)
				return true;
		} catch (Exception e) {
			return false;
		}

		return false;
	}

	private boolean createDatabase() {
		if (databaseExists())
			return true;

		try {
			HttpPut put = new HttpPut(this.getDatabaseUri());
			put.setHeader("Content-Type", "application/json");
			HttpResponse response = httpClient.execute(put);
			EntityUtils.consume(response.getEntity());
			if (response.getStatusLine().getStatusCode() == 201)
				return true;
		} catch (Exception e) {
			return false;
		}

		return false;
	}
}
