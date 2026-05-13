#include "urma_1113_check_valid_sgl_empty_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1113CheckValidSglEmptyInvalidParam> g_urma("urma_1113");

bool Urma1113CheckValidSglEmptyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"sge is a null pointer."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1113CheckValidSglEmptyInvalidParam::GetName() const
{
    return "check_valid_sgl 空指针参数非法";
}

std::string Urma1113CheckValidSglEmptyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `sg.sge == NULL || sg.sge[i].addr == 0`；该路径返回 -1";
}

RootCause Urma1113CheckValidSglEmptyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1113CheckValidSglEmptyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1113CheckValidSglEmptyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：sge is a null pointer.";
}

std::string Urma1113CheckValidSglEmptyInvalidParam::GetId() const
{
    return "urma_1113";
}
} // namespace diag
