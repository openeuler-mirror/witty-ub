#include "urma_failure_177.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure177> g_urma("urma_177");

bool UrmaFailure177::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_alloc_jfr") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure177::GetName() const
{
    return "URMA context、dev_fd、JFR、配置参数无效导致分配JFR失败";
}

std::string UrmaFailure177::GetRootCauseDesc() const
{
    return "urma_cmd_alloc_jfr用于分配JFR，调用方传入的URMA "
           "context、dev_fd、JFR、配置参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure177::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure177::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure177::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_alloc_jfr，Invalid parameter。";
}

std::string UrmaFailure177::GetId() const
{
    return "urma_177";
}
} // namespace diag
