#include "urma_0349_urma_cmd_active_jfc_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0349UrmaCmdActiveJfcInvalidParam> g_urma("urma_0349");

bool Urma0349UrmaCmdActiveJfcInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0349UrmaCmdActiveJfcInvalidParam::GetName() const
{
    return "urma_cmd_active_jfc 参数非法";
}

std::string Urma0349UrmaCmdActiveJfcInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfc == NULL || jfc->urma_ctx == NULL || jfc->urma_ctx->dev_fd < "
           "0`；该路径返回 -1";
}

RootCause Urma0349UrmaCmdActiveJfcInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0349UrmaCmdActiveJfcInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0349UrmaCmdActiveJfcInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0349UrmaCmdActiveJfcInvalidParam::GetId() const
{
    return "urma_0349";
}
} // namespace diag
