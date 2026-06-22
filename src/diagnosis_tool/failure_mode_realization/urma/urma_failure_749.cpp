#include "urma_failure_749.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure749> g_urma("urma_749");

bool UrmaFailure749::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("check_valid_jfr_wr") != std::string::npos &&
           message.find("There are invalid parameters.") != std::string::npos;
}

std::string UrmaFailure749::GetName() const
{
    return "valid、JFR、工作请求无效导致校验valid、JFR、工作请求失败";
}

std::string UrmaFailure749::GetRootCauseDesc() const
{
    return "check_valid_jfr_"
           "wr用于校验valid、JFR、工作请求，调用方传入的valid、JFR、工作请求不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure749::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure749::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure749::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：check_valid_jfr_wr，There are invalid parameters.。";
}

std::string UrmaFailure749::GetId() const
{
    return "urma_749";
}
} // namespace diag
