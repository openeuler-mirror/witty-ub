#include "urma_failure_609.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure609> g_urma("urma_609");

bool UrmaFailure609::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_create_context") != std::string::npos &&
           message.find("Failed to query eid.") != std::string::npos;
}

std::string UrmaFailure609::GetName() const
{
    return "下层查询返回失败导致创建context失败";
}

std::string UrmaFailure609::GetRootCauseDesc() const
{
    return "urma_cmd_create_"
           "context需要从provider、驱动或缓存中获取context状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure609::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure609::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure609::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_create_context，Failed to query eid.。";
}

std::string UrmaFailure609::GetId() const
{
    return "urma_609";
}
} // namespace diag
