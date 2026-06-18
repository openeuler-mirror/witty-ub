#include "urma_failure_287.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure287> g_urma("urma_287");

bool UrmaFailure287::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_context") != std::string::npos &&
           message.find("Failed to query eid.") != std::string::npos;
}

std::string UrmaFailure287::GetName() const
{
    return "下层查询返回失败导致创建context失败";
}

std::string UrmaFailure287::GetRootCauseDesc() const
{
    return "urma_create_context需要从provider、驱动或缓存中获取context状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure287::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure287::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string UrmaFailure287::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_context，Failed to query eid.。";
}

std::string UrmaFailure287::GetId() const
{
    return "urma_287";
}
} // namespace diag
