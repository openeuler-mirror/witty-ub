#include "urma_0608_urma_advise_jfr_invalid_param_ops_null_ops_advise_jfr.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0608UrmaAdviseJfrInvalidParamOpsNullOpsAdviseJfr> g_urma("urma_0608");

bool Urma0608UrmaAdviseJfrInvalidParamOpsNullOpsAdviseJfr::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0608UrmaAdviseJfrInvalidParamOpsNullOpsAdviseJfr::GetName() const
{
    return "urma_advise_jfr 参数非法（ops == NULL || ops->advise_jfr == NULL）";
}

std::string Urma0608UrmaAdviseJfrInvalidParamOpsNullOpsAdviseJfr::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ops == NULL || ops->advise_jfr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0608UrmaAdviseJfrInvalidParamOpsNullOpsAdviseJfr::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0608UrmaAdviseJfrInvalidParamOpsNullOpsAdviseJfr::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0608UrmaAdviseJfrInvalidParamOpsNullOpsAdviseJfr::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0608UrmaAdviseJfrInvalidParamOpsNullOpsAdviseJfr::GetId() const
{
    return "urma_0608";
}
} // namespace diag
