#include "urma_failure_245.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure245> g_urma("urma_245");

bool UrmaFailure245::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_jfs_opt") != std::string::npos &&
           message.find("Failed to exec ops->get_jfs_opt.") != std::string::npos;
}

std::string UrmaFailure245::GetName() const
{
    return "下层查询返回失败导致获取JFS失败";
}

std::string UrmaFailure245::GetRootCauseDesc() const
{
    return "urma_get_jfs_opt需要从provider、驱动或缓存中获取JFS状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure245::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure245::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure245::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_jfs_opt，Failed to exec ops->get_jfs_opt.。";
}

std::string UrmaFailure245::GetId() const
{
    return "urma_245";
}
} // namespace diag
