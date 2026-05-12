#include "urma_0611_urma_advise_jfr_async_invalid_param_ops_null_ops_advise.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0611UrmaAdviseJfrAsyncInvalidParamOpsNullOpsAdvise> g_urma("urma_0611");

bool Urma0611UrmaAdviseJfrAsyncInvalidParamOpsNullOpsAdvise::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0611UrmaAdviseJfrAsyncInvalidParamOpsNullOpsAdvise::GetName() const
{
    return "urma_advise_jfr_async 参数非法（ops == NULL || ops->advise_jfr_async == NULL）";
}

std::string Urma0611UrmaAdviseJfrAsyncInvalidParamOpsNullOpsAdvise::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ops == NULL || ops->advise_jfr_async == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0611UrmaAdviseJfrAsyncInvalidParamOpsNullOpsAdvise::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0611UrmaAdviseJfrAsyncInvalidParamOpsNullOpsAdvise::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0611UrmaAdviseJfrAsyncInvalidParamOpsNullOpsAdvise::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0611UrmaAdviseJfrAsyncInvalidParamOpsNullOpsAdvise::GetId() const
{
    return "urma_0611";
}
} // namespace diag
