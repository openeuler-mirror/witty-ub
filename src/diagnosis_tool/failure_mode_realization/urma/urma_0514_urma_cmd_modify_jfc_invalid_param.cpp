#include "urma_0514_urma_cmd_modify_jfc_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0514UrmaCmdModifyJfcInvalidParam> g_urma("urma_0514");

bool Urma0514UrmaCmdModifyJfcInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0514UrmaCmdModifyJfcInvalidParam::GetName() const
{
    return "urma_cmd_modify_jfc 参数非法";
}

std::string Urma0514UrmaCmdModifyJfcInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfc == NULL || jfc->urma_ctx == NULL || jfc->urma_ctx->dev_fd < 0 || attr == "
           "NULL`；该路径返回 -1";
}

RootCause Urma0514UrmaCmdModifyJfcInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0514UrmaCmdModifyJfcInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0514UrmaCmdModifyJfcInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0514UrmaCmdModifyJfcInvalidParam::GetId() const
{
    return "urma_0514";
}
} // namespace diag
