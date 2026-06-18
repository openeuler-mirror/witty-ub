#include "urma_failure_074.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure074> g_urma("urma_074");

bool UrmaFailure074::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_unimport_jfr") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure074::GetName() const
{
    return "tjfr无效导致取消导入JFR失败";
}

std::string UrmaFailure074::GetRootCauseDesc() const
{
    return "urma_cmd_unimport_jfr用于取消导入JFR，调用方传入的tjfr不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure074::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure074::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure074::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_unimport_jfr，Invalid parameter。";
}

std::string UrmaFailure074::GetId() const
{
    return "urma_074";
}
} // namespace diag
