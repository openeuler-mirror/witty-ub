#include "urma_0868_check_valid_jfr_wr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0868CheckValidJfrWrInvalidParam> g_urma("urma_0868");

bool Urma0868CheckValidJfrWrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"There are invalid parameters."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0868CheckValidJfrWrInvalidParam::GetName() const
{
    return "check_valid_jfr_wr 参数非法";
}

std::string Urma0868CheckValidJfrWrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfr == NULL || wr == NULL`；该路径返回 -1";
}

RootCause Urma0868CheckValidJfrWrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0868CheckValidJfrWrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0868CheckValidJfrWrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：There are invalid parameters.";
}

std::string Urma0868CheckValidJfrWrInvalidParam::GetId() const
{
    return "urma_0868";
}
} // namespace diag
