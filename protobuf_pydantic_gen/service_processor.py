"""
Service and HTTP metadata extraction utilities
"""
import logging
from typing import Dict, Any, List, Optional
from google.protobuf import descriptor_pb2
from google.protobuf.json_format import MessageToDict
from google.api import annotations_pb2
from .models import Service, ServiceMethod

logger = logging.getLogger(__name__)


class ServiceProcessor:
    """Processes gRPC service definitions"""

    def extract_services_from_file(
        self,
        proto_file: descriptor_pb2.FileDescriptorProto
    ) -> List[Service]:
        """
        Extract all services from a protobuf file

        Args:
            proto_file: Protobuf file descriptor

        Returns:
            List of extracted services
        """
        services = []

        for service_desc in proto_file.service:
            methods = []

            for method_desc in service_desc.method:
                try:
                    method = self._extract_method(
                        method_desc, proto_file.package, service_desc.name)
                    methods.append(method)
                except Exception as e:
                    logger.error(
                        f"Error extracting method {method_desc.name}: {e}")
                    continue

            service = Service(
                name=service_desc.name,
                methods=methods,
                package=proto_file.package
            )
            services.append(service)

        return services

    def _extract_method(
        self,
        method: descriptor_pb2.MethodDescriptorProto,
        package: str,
        service_name: str
    ) -> ServiceMethod:
        """Extract method information"""
        streaming_info = self._get_streaming_info(method)
        http_info = self._extract_http_info(method)

        # Generate full method name
        service_full_name = f"/{package}.{service_name}" if package else service_name
        method_full_name = f"{service_full_name}/{method.name}"

        return ServiceMethod(
            name=method.name,
            input_type=method.input_type,
            output_type=method.output_type,
            streaming_type=streaming_info["streaming_type"],
            method_full_name=method_full_name,
            http_info=http_info,
            options=MessageToDict(method.options) if method.options else None
        )

    def _get_streaming_info(self, method: descriptor_pb2.MethodDescriptorProto) -> Dict[str, Any]:
        """
        Get streaming information for a method

        Returns:
            Dict containing streaming details
        """
        client_streaming = method.client_streaming
        server_streaming = method.server_streaming

        # Determine streaming type
        if client_streaming and server_streaming:
            streaming_type = "bidirectional_streaming"
        elif client_streaming:
            streaming_type = "client_streaming"
        elif server_streaming:
            streaming_type = "server_streaming"
        else:
            streaming_type = "unary"

        return {
            "client_streaming": client_streaming,
            "server_streaming": server_streaming,
            "streaming_type": streaming_type,
            "is_streaming": client_streaming or server_streaming,
        }

    def _extract_http_info(self, method: descriptor_pb2.MethodDescriptorProto) -> Optional[Dict[str, Any]]:
        """Extract HTTP annotation information"""
        try:
            if not method.options.HasExtension(annotations_pb2.http):
                return None

            http_rule = method.options.Extensions[annotations_pb2.http]
            http_info = {}

            # Get HTTP method and path
            if http_rule.HasField("get"):
                http_info["method"] = "GET"
                http_info["path"] = http_rule.get
            elif http_rule.HasField("post"):
                http_info["method"] = "POST"
                http_info["path"] = http_rule.post
            elif http_rule.HasField("put"):
                http_info["method"] = "PUT"
                http_info["path"] = http_rule.put
            elif http_rule.HasField("delete"):
                http_info["method"] = "DELETE"
                http_info["path"] = http_rule.delete
            elif http_rule.HasField("patch"):
                http_info["method"] = "PATCH"
                http_info["path"] = http_rule.patch
            elif http_rule.HasField("custom"):
                http_info["method"] = http_rule.custom.kind
                http_info["path"] = http_rule.custom.path

            # Get body configuration
            if http_rule.body:
                http_info["body"] = http_rule.body

            # Get response body configuration
            if http_rule.response_body:
                http_info["response_body"] = http_rule.response_body

            # Get additional bindings
            if http_rule.additional_bindings:
                additional = []
                for binding in http_rule.additional_bindings:
                    additional.append(self._extract_http_rule(binding))
                http_info["additional_bindings"] = additional

            return http_info

        except Exception as e:
            logger.error(
                f"Error extracting HTTP info for method {method.name}: {e}")
            return None

    def _extract_http_rule(self, rule) -> Dict[str, Any]:
        """Extract HTTP rule information"""
        rule_info = {}

        if rule.HasField("get"):
            rule_info["method"] = "GET"
            rule_info["path"] = rule.get
        elif rule.HasField("post"):
            rule_info["method"] = "POST"
            rule_info["path"] = rule.post
        elif rule.HasField("put"):
            rule_info["method"] = "PUT"
            rule_info["path"] = rule.put
        elif rule.HasField("delete"):
            rule_info["method"] = "DELETE"
            rule_info["path"] = rule.delete
        elif rule.HasField("patch"):
            rule_info["method"] = "PATCH"
            rule_info["path"] = rule.patch

        if rule.body:
            rule_info["body"] = rule.body

        return rule_info

    def services_to_dict(self, services: List[Service]) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Convert services to dictionary format for JSON output"""
        services_dict = {}

        for service in services:
            methods_dict = {}

            for method in service.methods:
                method_dict = {
                    "input_type": method.input_type,
                    "output_type": method.output_type,
                    "streaming_type": method.streaming_type,
                    "method_full_name": method.method_full_name,
                }

                if method.options:
                    method_dict["options"] = method.options

                if method.http_info:
                    method_dict["http"] = method.http_info

                methods_dict[method.name] = method_dict

            services_dict[service.name] = methods_dict

        return services_dict
