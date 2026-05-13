#include "urma_0369_urma_cmd_alloc_jfr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0369UrmaCmdAllocJfrInvalidParam> g_urma("urma_0369");

bool Urma0369UrmaCmdAllocJfrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0369UrmaCmdAllocJfrInvalidParam::GetName() const
{
    return "urma_cmd_alloc_jfr 参数非法";
}

std::string Urma0369UrmaCmdAllocJfrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev_fd < 0 || jfr == NULL || cfg == NULL`；该路径返回 -1";
}

RootCause Urma0369UrmaCmdAllocJfrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0369UrmaCmdAllocJfrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0369UrmaCmdAllocJfrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0369UrmaCmdAllocJfrInvalidParam::GetId() const
{
    return "urma_0369";
}
} // namespace diag
