#include "urma_failure_228.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure228> g_urma("urma_228");

bool UrmaFailure228::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("get_comp_urma_jetty_id") != std::string::npos &&
           message.find("Failed to get_comp_urma_jetty, Invalid type:") != std::string::npos;
}

std::string UrmaFailure228::GetName() const
{
    return "下层查询返回失败导致获取COMP、URMA、Jetty失败";
}

std::string UrmaFailure228::GetRootCauseDesc() const
{
    return "get_comp_urma_jetty_"
           "id需要从provider、驱动或缓存中获取COMP、URMA、Jetty状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure228::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure228::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure228::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：get_comp_urma_jetty_id，Failed to get_comp_urma_jetty, Invalid type:。";
}

std::string UrmaFailure228::GetId() const
{
    return "urma_228";
}
} // namespace diag
