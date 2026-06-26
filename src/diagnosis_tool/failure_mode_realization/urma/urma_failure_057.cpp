#include "urma_failure_057.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure057> g_urma("urma_057");

bool UrmaFailure057::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_import_jetty") != std::string::npos &&
           message.find("Failed to import health check seg for jetty") != std::string::npos;
}

std::string UrmaFailure057::GetName() const
{
    return "下层注册或导入返回失败导致导入Jetty失败";
}

std::string UrmaFailure057::GetRootCauseDesc() const
{
    return "bondp_import_jetty在导入Jetty时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure057::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure057::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure057::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_jetty，Failed to import health check seg for jetty。";
}

std::string UrmaFailure057::GetId() const
{
    return "urma_057";
}
} // namespace diag
