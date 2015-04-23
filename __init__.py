import json
from flask import Blueprint,  abort, request, make_response, render_template, jsonify
import requests
import requests_cache
from lxml import etree
import re

ahab = Blueprint('ahab', __name__, template_folder='templates')
configuration = json.load(ahab.open_resource("configurations/cts.json", "r"))

if configuration["cache"]:
    requests_cache.install_cache(
        ahab.root_path+"/capitains-ahab",
        backend="sqlite",
        expire_after=configuration["cache.time"]
    )

space_normalizer = re.compile(r'\s{2,}')


def argsToInt(arg):
    try:
        return int(arg)
    except:
        return None


def request_wants_json():
    best = request.accept_mimetypes.best_match(['application/json'])
    return best == 'application/json'


def requesting(endpoint, params):
    try:
        r = requests.get(endpoint, params=params)
        if r.status_code != 200:
            abort(404)
        return r.text
    except:
        abort(404)
    abort(404)


def makeUrn(namespace, work=None):
    if work is not None and len(work) > 0:
        return "urn:cts:{0}:{1}".format(namespace, ".".join(work))
    else:
        return "urn:cts:{0}".format(namespace)


@ahab.route("/cts/api", methods=["GET"])
def xq():
    response = make_response(requesting(configuration["endpoint"], params=request.args.to_dict()))
    response.headers["Content-Type"] = "application/xml"
    return response


"""
RESTful API
"""
if configuration["restfull"] is True:
    @ahab.route("/cts/rest/v1.0/<inventory>", methods=["GET"])
    def getCapabilities(inventory):
        return requesting(configuration["endpoint"], params={"request": "GetCapabilities", "inv": inventory})

    @ahab.route("/cts/rest/v1.0/<inventory>/<namespace>", methods=["GET"])
    def getNamespaceCapabilities(inventory, namespace):
        return requesting(configuration["endpoint"], params={
            "request": "GetCapabilities",
            "inv": inventory,
            "urn": makeUrn(namespace)
        })

    @ahab.route("/cts/rest/v1.0/<inventory>/<namespace>/<textgroup>", methods=["GET"])
    def getTextGroupCapabilities(inventory, namespace, textgroup):
        return requesting(configuration["endpoint"], params={
            "request": "GetCapabilities",
            "inv": inventory,
            "urn": makeUrn(namespace, [textgroup])
        })

    @ahab.route("/cts/rest/v1.0/<inventory>/<namespace>/<textgroup>/<work>", methods=["GET"])
    def getWorkCapabilities(inventory, namespace, textgroup, work):
        return requesting(
            configuration["endpoint"],
            params={
                "request": "GetCapabilities",
                "inv": inventory,
                "urn": makeUrn(namespace, [textgroup, work])
            }
        )

    @ahab.route("/cts/rest/v1.0/<inventory>/<namespace>/<textgroup>/<work>/<text>/validReff", methods=["GET"])
    def getWorkValidReff(inventory, namespace, textgroup, work, text):
        return requesting(
            configuration["endpoint"],
            params={
                "request": "GetValidReff",
                "inv": inventory,
                "urn": "urn:cts:{0}:{1}.{2}.{3}".format(namespace, textgroup, work, text),
                "level": request.args.get("level")
            }
        )

    @ahab.route("/cts/rest/v1.0/<inventory>/<namespace>/<textgroup>/<work>/<text>/passage/<ref>", methods=["GET"])
    def getWorkPassage(inventory, namespace, textgroup, work, text, ref):
        return requesting(
            configuration["endpoint"],
            params={
                "request": "GetPassage",
                "inv": inventory,
                "urn": "urn:cts:{0}:{1}.{2}.{3}:{4}".format(namespace, textgroup, work, text, ref),
                "level": request.args.get("level")
            }
        )

    @ahab.route("/cts/rest/v1.0/<inventory>/<namespace>/<textgroup>/<work>/<text>/passagePlus/<ref>", methods=["GET"])
    def getWorkPassagePlus(inventory, namespace, textgroup, work, text, ref):
        return requesting(
            configuration["endpoint"],
            params={
                "request": "GetPassagePlus",
                "inv": inventory,
                "urn": "urn:cts:{0}:{1}.{2}.{3}:{4}".format(namespace, textgroup, work, text, ref),
                "level": request.args.get("level")
            }
        )

    @ahab.route("/cts/rest/v1.0/<inventory>/<namespace>/<textgroup>/<work>/<text>/firstPassage", methods=["GET"])
    def getWorkFirstPassage(inventory, namespace, textgroup, work, text):
        return requesting(
            configuration["endpoint"],
            params={
                "request": "GetFirstPassage",
                "inv": inventory,
                "urn": "urn:cts:{0}:{1}.{2}.{3}:{4}".format(namespace, textgroup, work, text),
                "level": request.args.get("level")
            }
        )

if "ahab.search" in configuration:
    @ahab.route("/ahab/rest/v1.0/search", methods=["GET"])
    def search():
        params = request.args.to_dict().copy()
        params.update({"request": "Search"})
        params.pop("start", None)
        params.pop("limit", None)

        response = requesting(
            configuration["ahab.endpoint"],
            params=params
        )
        xml = etree.fromstring(response)
        start = argsToInt(request.args.get("start")) or 1
        limit = argsToInt(request.args.get("limit")) or 10

        results = xml.find(".//ahab:results", {"ahab": "http://github.com/capitains/ahab"})
        resultSet = results.findall("./ahab:result", {"ahab": "http://github.com/capitains/ahab"})
        count = results.get("{http://github.com/capitains/ahab}count")

        limitedResults = resultSet[start-1:start-1+limit]

        if request_wants_json():
            jsonResults = []
            for result in limitedResults:
                jsonResults.append({
                    "urn": result.find("ahab:urn", {"ahab": "http://github.com/capitains/ahab"}).text,
                    "passage": result.find("ahab:passageUrn", {"ahab": "http://github.com/capitains/ahab"}).text,
                    "text": {
                        "previous": space_normalizer.sub(
                            "",
                            "".join([x for x in result.find("ahab:text//span[@class='previous']", {"ahab": "http://github.com/capitains/ahab"}).itertext()])
                        ),
                        "hi": space_normalizer.sub(
                            "",
                            "".join([x for x in result.find("ahab:text//span[@class='hi']", {"ahab": "http://github.com/capitains/ahab"}).itertext()])
                        ),
                        "after": space_normalizer.sub(
                            "",
                            "".join([x for x in result.find("ahab:text//span[@class='following']", {"ahab": "http://github.com/capitains/ahab"}).itertext()])
                        )
                    }
                })

            data = {
                "request": {
                    "query": request.args.get("query"),
                    "urn": request.args.get("urn") or None
                },
                "reply": {
                    "offset": start,
                    "limit": limit,
                    "count": count,
                    "results": jsonResults
                }
            }
            return jsonify(data)

        """
            XML Response
        """
        limitedResults = [
            {
                "urn": result.find("ahab:urn", {"ahab": "http://github.com/capitains/ahab"}).text,
                "version": result.find("ahab:passageUrn", {"ahab": "http://github.com/capitains/ahab"}).text,
                "text": str(etree.tostring(result.find("ahab:text", {"ahab": "http://github.com/capitains/ahab"})[0]), "utf-8")
            }
            for result in limitedResults
        ]
        responseXml = render_template(
            'search.xml',
            query=request.args.get("query"),
            urn=request.args.get("urn") or None,
            start=start,
            limit=limit,
            count=count,
            results=limitedResults
        )
        response = make_response(responseXml)
        response.headers["Content-Type"] = "application/xml"
        return response

if "ahab.permalink" in configuration:
    @ahab.route("/ahab/rest/v1.0/permalink/<ref>", methods=["GET"])
    def permalink(ref):
        r = requests.get(configuration["ahab.endpoint"], params={"request": "permalink", "urn": ref})
        xml = etree.fromstring(r.text)
        if r.status_code != 200:
            abort(404)
        return requesting(
            configuration["endpoint"],
            params={
                "request": xml.find(".//ahab:reply/ahab:request", {"ahab": "http://github.com/capitains/ahab"}).text,
                "urn": xml.find(".//ahab:reply/ahab:urn", {"ahab": "http://github.com/capitains/ahab"}).text,
                "inv": xml.find(".//ahab:reply/ahab:inventory", {"ahab": "http://github.com/capitains/ahab"}).text
            }
        )


@ahab.route("/ahab/rest/v1.0/reset_cache", methods=["GET"])
def reset_cache():
    if request.args.get("key") == configuration["cache.reset_key"]:
        requests_cache.core.clear()
        return ""
    else:
        abort(404)
