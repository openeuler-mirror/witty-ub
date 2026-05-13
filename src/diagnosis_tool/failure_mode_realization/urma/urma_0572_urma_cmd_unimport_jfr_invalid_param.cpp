#include "urma_0572_urma_cmd_unimport_jfr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0572UrmaCmdUnimportJfrInvalidParam> g_urma("urma_0572");

bool Urma0572UrmaCmdUnimportJfrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0572UrmaCmdUnimportJfrInvalidParam::GetName() const
{
    return "urma_cmd_unimport_jfr 参数非法";
}

std::string Urma0572UrmaCmdUnimportJfrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `tjfr == NULL`；该路径返回 -1";
}

RootCause Urma0572UrmaCmdUnimportJfrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0572UrmaCmdUnimportJfrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0572UrmaCmdUnimportJfrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0572UrmaCmdUnimportJfrInvalidParam::GetId() const
{
    return "urma_0572";
}
} // namespace diag
