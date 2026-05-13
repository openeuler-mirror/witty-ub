#include "urma_0598_urma_active_jfs_resource_failure_jfs_urma_jfs_opt_is.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0598UrmaActiveJfsResourceFailureJfsUrmaJfsOptIs> g_urma("urma_0598");

bool Urma0598UrmaActiveJfsResourceFailureJfsUrmaJfsOptIs::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jfs state is wrong in active_jfs."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0598UrmaActiveJfsResourceFailureJfsUrmaJfsOptIs::GetName() const
{
    return "urma_active_jfs 激活资源失败（jfs->urma_jfs_opt.is_actived == true）";
}

std::string Urma0598UrmaActiveJfsResourceFailureJfsUrmaJfsOptIs::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0598UrmaActiveJfsResourceFailureJfsUrmaJfsOptIs::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0598UrmaActiveJfsResourceFailureJfsUrmaJfsOptIs::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0598UrmaActiveJfsResourceFailureJfsUrmaJfsOptIs::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfs state is wrong in active_jfs.";
}

std::string Urma0598UrmaActiveJfsResourceFailureJfsUrmaJfsOptIs::GetId() const
{
    return "urma_0598";
}
} // namespace diag
