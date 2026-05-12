#include "urma_0699_urma_deactive_jfs_resource_failure_jfs_urma_jfs_opt_is.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0699UrmaDeactiveJfsResourceFailureJfsUrmaJfsOptIs> g_urma("urma_0699");

bool Urma0699UrmaDeactiveJfsResourceFailureJfsUrmaJfsOptIs::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jfs state is wrong in deactive_jfs."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0699UrmaDeactiveJfsResourceFailureJfsUrmaJfsOptIs::GetName() const
{
    return "urma_deactive_jfs 激活资源失败（jfs->urma_jfs_opt.is_actived == false）";
}

std::string Urma0699UrmaDeactiveJfsResourceFailureJfsUrmaJfsOptIs::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0699UrmaDeactiveJfsResourceFailureJfsUrmaJfsOptIs::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0699UrmaDeactiveJfsResourceFailureJfsUrmaJfsOptIs::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0699UrmaDeactiveJfsResourceFailureJfsUrmaJfsOptIs::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfs state is wrong in deactive_jfs.";
}

std::string Urma0699UrmaDeactiveJfsResourceFailureJfsUrmaJfsOptIs::GetId() const
{
    return "urma_0699";
}
} // namespace diag
