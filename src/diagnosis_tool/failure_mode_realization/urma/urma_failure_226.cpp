#include "urma_failure_226.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure226> g_urma("urma_226");

bool UrmaFailure226::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_get_async_event") != std::string::npos &&
           message.find("failed to get invalid jetty.") != std::string::npos;
}

std::string UrmaFailure226::GetName() const
{
    return "下层查询返回失败导致获取event失败";
}

std::string UrmaFailure226::GetRootCauseDesc() const
{
    return "bondp_get_async_event需要从provider、驱动或缓存中获取event状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure226::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure226::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure226::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_get_async_event，failed to get invalid jetty.。";
}

std::string UrmaFailure226::GetId() const
{
    return "urma_226";
}
} // namespace diag
