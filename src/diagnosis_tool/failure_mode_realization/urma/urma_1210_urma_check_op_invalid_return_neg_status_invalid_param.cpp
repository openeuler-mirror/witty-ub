#include "urma_1210_urma_check_op_invalid_return_neg_status_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1210UrmaCheckOpInvalidReturnNegStatusInvalidParam> g_urma("urma_1210");

bool Urma1210UrmaCheckOpInvalidReturnNegStatusInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1210UrmaCheckOpInvalidReturnNegStatusInvalidParam::GetName() const
{
    return "URMA_CHECK_OP_INVALID_RETURN_NEG_STATUS 参数非法";
}

std::string Urma1210UrmaCheckOpInvalidReturnNegStatusInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败；该路径返回 -URMA_EINVAL";
}

RootCause Urma1210UrmaCheckOpInvalidReturnNegStatusInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1210UrmaCheckOpInvalidReturnNegStatusInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1210UrmaCheckOpInvalidReturnNegStatusInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1210UrmaCheckOpInvalidReturnNegStatusInvalidParam::GetId() const
{
    return "urma_1210";
}
} // namespace diag
