#include "urma_1212_urma_check_op_invalid_return_pointer_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1212UrmaCheckOpInvalidReturnPointerInvalidParam> g_urma("urma_1212");

bool Urma1212UrmaCheckOpInvalidReturnPointerInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1212UrmaCheckOpInvalidReturnPointerInvalidParam::GetName() const
{
    return "URMA_CHECK_OP_INVALID_RETURN_POINTER 参数非法";
}

std::string Urma1212UrmaCheckOpInvalidReturnPointerInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败；该路径返回 NULL";
}

RootCause Urma1212UrmaCheckOpInvalidReturnPointerInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1212UrmaCheckOpInvalidReturnPointerInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1212UrmaCheckOpInvalidReturnPointerInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1212UrmaCheckOpInvalidReturnPointerInvalidParam::GetId() const
{
    return "urma_1212";
}
} // namespace diag
