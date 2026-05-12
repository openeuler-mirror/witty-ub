#include "urma_1129_bondp_delete_vseg_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1129BondpDeleteVsegInvalidParam> g_urma("urma_1129");

bool Urma1129BondpDeleteVsegInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"invalid param."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1129BondpDeleteVsegInvalidParam::GetName() const
{
    return "bondp_delete_vseg invalid param.";
}

std::string Urma1129BondpDeleteVsegInvalidParam::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `bdp_seg == NULL`；该路径返回 URMA_FAIL";
}

RootCause Urma1129BondpDeleteVsegInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1129BondpDeleteVsegInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1129BondpDeleteVsegInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：invalid param.";
}

std::string Urma1129BondpDeleteVsegInvalidParam::GetId() const
{
    return "urma_1129";
}
} // namespace diag
