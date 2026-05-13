#include "urma_1116_urma_recv_invalid_param_check_valid_jfr_wr_jfr_wr.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1116UrmaRecvInvalidParamCheckValidJfrWrJfrWr> g_urma("urma_1116");

bool Urma1116UrmaRecvInvalidParamCheckValidJfrWrJfrWr::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"There are invalid parameters."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1116UrmaRecvInvalidParamCheckValidJfrWrJfrWr::GetName() const
{
    return "urma_recv 参数非法（check_valid_jfr_wr(jfr, &wr) != 0）";
}

std::string Urma1116UrmaRecvInvalidParamCheckValidJfrWrJfrWr::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `check_valid_jfr_wr(jfr, &wr) != 0`；该路径返回 URMA_FAIL";
}

RootCause Urma1116UrmaRecvInvalidParamCheckValidJfrWrJfrWr::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1116UrmaRecvInvalidParamCheckValidJfrWrJfrWr::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1116UrmaRecvInvalidParamCheckValidJfrWrJfrWr::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：There are invalid parameters.";
}

std::string Urma1116UrmaRecvInvalidParamCheckValidJfrWrJfrWr::GetId() const
{
    return "urma_1116";
}
} // namespace diag
