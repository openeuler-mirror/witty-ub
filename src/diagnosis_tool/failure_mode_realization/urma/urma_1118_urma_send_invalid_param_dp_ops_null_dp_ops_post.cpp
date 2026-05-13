#include "urma_1118_urma_send_invalid_param_dp_ops_null_dp_ops_post.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1118UrmaSendInvalidParamDpOpsNullDpOpsPost> g_urma("urma_1118");

bool Urma1118UrmaSendInvalidParamDpOpsNullDpOpsPost::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1118UrmaSendInvalidParamDpOpsNullDpOpsPost::GetName() const
{
    return "urma_send 参数非法（dp_ops == NULL || dp_ops->post_jfs_wr == NULL）";
}

std::string Urma1118UrmaSendInvalidParamDpOpsNullDpOpsPost::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `dp_ops == NULL || dp_ops->post_jfs_wr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma1118UrmaSendInvalidParamDpOpsNullDpOpsPost::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1118UrmaSendInvalidParamDpOpsNullDpOpsPost::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1118UrmaSendInvalidParamDpOpsNullDpOpsPost::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1118UrmaSendInvalidParamDpOpsNullDpOpsPost::GetId() const
{
    return "urma_1118";
}
} // namespace diag
