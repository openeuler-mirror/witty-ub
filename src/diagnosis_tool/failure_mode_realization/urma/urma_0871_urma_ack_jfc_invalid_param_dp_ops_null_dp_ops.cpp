#include "urma_0871_urma_ack_jfc_invalid_param_dp_ops_null_dp_ops.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0871UrmaAckJfcInvalidParamDpOpsNullDpOps> g_urma("urma_0871");

bool Urma0871UrmaAckJfcInvalidParamDpOpsNullDpOps::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0871UrmaAckJfcInvalidParamDpOpsNullDpOps::GetName() const
{
    return "urma_ack_jfc 参数非法（dp_ops == NULL || dp_ops->ack_jfc == NULL）";
}

std::string Urma0871UrmaAckJfcInvalidParamDpOpsNullDpOps::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `dp_ops == NULL || dp_ops->ack_jfc == NULL`";
}

RootCause Urma0871UrmaAckJfcInvalidParamDpOpsNullDpOps::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0871UrmaAckJfcInvalidParamDpOpsNullDpOps::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0871UrmaAckJfcInvalidParamDpOpsNullDpOps::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0871UrmaAckJfcInvalidParamDpOpsNullDpOps::GetId() const
{
    return "urma_0871";
}
} // namespace diag
