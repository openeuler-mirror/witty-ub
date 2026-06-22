#include "urma_failure_295.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure295> g_urma("urma_295");

bool UrmaFailure295::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_jetty") != std::string::npos &&
           message.find("Failed to register health check seg for jetty creation") != std::string::npos;
}

std::string UrmaFailure295::GetName() const
{
    return "下层注册或导入返回失败导致创建Jetty失败";
}

std::string UrmaFailure295::GetRootCauseDesc() const
{
    return "bondp_create_jetty在创建Jetty时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure295::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure295::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure295::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_jetty，Failed to register health check seg for jetty "
           "creation。";
}

std::string UrmaFailure295::GetId() const
{
    return "urma_295";
}
} // namespace diag
