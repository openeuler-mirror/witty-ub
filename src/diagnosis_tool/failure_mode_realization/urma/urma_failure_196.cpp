#include "urma_failure_196.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure196> g_urma("urma_196");

bool UrmaFailure196::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_alloc_jfr") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure196::GetName() const
{
    return "URMA context、配置参数、JFR、JFC无效导致分配JFR失败";
}

std::string UrmaFailure196::GetRootCauseDesc() const
{
    return "urma_alloc_jfr用于分配JFR，调用方传入的URMA "
           "context、配置参数、JFR、JFC不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure196::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure196::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure196::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_jfr，Invalid parameter.。";
}

std::string UrmaFailure196::GetId() const
{
    return "urma_196";
}
} // namespace diag
