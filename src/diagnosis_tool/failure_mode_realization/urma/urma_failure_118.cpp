#include "urma_failure_118.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure118> g_urma("urma_118");

bool UrmaFailure118::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_unimport_jetty_async") != std::string::npos &&
           message.find("Failed to unimport jetty.") != std::string::npos;
}

std::string UrmaFailure118::GetName() const
{
    return "下层注册或导入返回失败导致取消导入Jetty失败";
}

std::string UrmaFailure118::GetRootCauseDesc() const
{
    return "urma_unimport_jetty_"
           "async在取消导入Jetty时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure118::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure118::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure118::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unimport_jetty_async，Failed to unimport jetty.。";
}

std::string UrmaFailure118::GetId() const
{
    return "urma_118";
}
} // namespace diag
