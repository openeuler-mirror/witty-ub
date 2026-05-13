#include "urma_0745_urma_delete_jfs_resource_delete_failure_jfs_urma_jfs_opt.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0745UrmaDeleteJfsResourceDeleteFailureJfsUrmaJfsOpt> g_urma("urma_0745");

bool Urma0745UrmaDeleteJfsResourceDeleteFailureJfsUrmaJfsOpt::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jfs is deactived, can not delete."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0745UrmaDeleteJfsResourceDeleteFailureJfsUrmaJfsOpt::GetName() const
{
    return "urma_delete_jfs 删除资源失败（jfs->urma_jfs_opt.is_actived == false）";
}

std::string Urma0745UrmaDeleteJfsResourceDeleteFailureJfsUrmaJfsOpt::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0745UrmaDeleteJfsResourceDeleteFailureJfsUrmaJfsOpt::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0745UrmaDeleteJfsResourceDeleteFailureJfsUrmaJfsOpt::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0745UrmaDeleteJfsResourceDeleteFailureJfsUrmaJfsOpt::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfs is deactived, can not delete.";
}

std::string Urma0745UrmaDeleteJfsResourceDeleteFailureJfsUrmaJfsOpt::GetId() const
{
    return "urma_0745";
}
} // namespace diag
