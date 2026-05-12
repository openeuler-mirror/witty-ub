#include "urma_0673_urma_create_jfce_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0673UrmaCreateJfceInvalidParam> g_urma("urma_0673");

bool Urma0673UrmaCreateJfceInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0673UrmaCreateJfceInvalidParam::GetName() const
{
    return "urma_create_jfce 参数非法";
}

std::string Urma0673UrmaCreateJfceInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL`；该路径返回 NULL";
}

RootCause Urma0673UrmaCreateJfceInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0673UrmaCreateJfceInvalidParam::GetFixSuggDesc() const
{
    return "当前预期不会出现，如果fd超规格可能导致失败，此时需要修改系统fd规格数，或者减小应用创建jfce的数量";
}

std::string Urma0673UrmaCreateJfceInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0673UrmaCreateJfceInvalidParam::GetId() const
{
    return "urma_0673";
}
} // namespace diag
