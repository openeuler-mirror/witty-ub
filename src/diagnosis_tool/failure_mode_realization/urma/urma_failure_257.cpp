#include "urma_failure_257.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure257> g_urma("urma_257");

bool UrmaFailure257::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_jetty_opt") != std::string::npos &&
           message.find("Failed to exec ops->get_jetty_opt.") != std::string::npos;
}

std::string UrmaFailure257::GetName() const
{
    return "下层查询返回失败导致获取Jetty失败";
}

std::string UrmaFailure257::GetRootCauseDesc() const
{
    return "urma_get_jetty_opt需要从provider、驱动或缓存中获取Jetty状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure257::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure257::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure257::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_jetty_opt，Failed to exec ops->get_jetty_opt.。";
}

std::string UrmaFailure257::GetId() const
{
    return "urma_257";
}
} // namespace diag
