#include "urma_1115_urma_recv_invalid_param_dp_ops_null_dp_ops_post.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1115UrmaRecvInvalidParamDpOpsNullDpOpsPost> g_urma("urma_1115");

bool Urma1115UrmaRecvInvalidParamDpOpsNullDpOpsPost::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1115UrmaRecvInvalidParamDpOpsNullDpOpsPost::GetName() const
{
    return "urma_recv 参数非法（dp_ops == NULL || dp_ops->post_jfr_wr == NULL || recv_tseg == NULL）";
}

std::string Urma1115UrmaRecvInvalidParamDpOpsNullDpOpsPost::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `dp_ops == NULL || dp_ops->post_jfr_wr == NULL || recv_tseg == "
           "NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma1115UrmaRecvInvalidParamDpOpsNullDpOpsPost::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1115UrmaRecvInvalidParamDpOpsNullDpOpsPost::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1115UrmaRecvInvalidParamDpOpsNullDpOpsPost::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1115UrmaRecvInvalidParamDpOpsNullDpOpsPost::GetId() const
{
    return "urma_1115";
}
} // namespace diag
