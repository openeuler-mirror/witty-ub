#include "urma_failure_690.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure690> g_urma("urma_690");

bool UrmaFailure690::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_modify_jfr") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure690::GetName() const
{
    return "JFR无效导致修改JFR失败";
}

std::string UrmaFailure690::GetRootCauseDesc() const
{
    return "urma_cmd_modify_jfr用于修改JFR，调用方传入的JFR不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure690::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure690::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure690::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_modify_jfr，Invalid parameter。";
}

std::string UrmaFailure690::GetId() const
{
    return "urma_690";
}
} // namespace diag
