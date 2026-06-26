#include "urma_failure_718.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure718> g_urma("urma_718");

bool UrmaFailure718::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_modify_jfr") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure718::GetName() const
{
    return "JFR、属性参数无效导致修改JFR失败";
}

std::string UrmaFailure718::GetRootCauseDesc() const
{
    return "urma_modify_jfr用于修改JFR，调用方传入的JFR、属性参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure718::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure718::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure718::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_modify_jfr，Invalid parameter.。";
}

std::string UrmaFailure718::GetId() const
{
    return "urma_718";
}
} // namespace diag
