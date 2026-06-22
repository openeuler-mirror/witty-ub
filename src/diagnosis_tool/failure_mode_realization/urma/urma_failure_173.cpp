#include "urma_failure_173.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure173> g_urma("urma_173");

bool UrmaFailure173::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_create_jfr") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure173::GetName() const
{
    return "URMA context、dev_fd、JFR、配置参数无效导致创建JFR失败";
}

std::string UrmaFailure173::GetRootCauseDesc() const
{
    return "urma_cmd_create_jfr用于创建JFR，调用方传入的URMA "
           "context、dev_fd、JFR、配置参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure173::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure173::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure173::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_create_jfr，Invalid parameter。";
}

std::string UrmaFailure173::GetId() const
{
    return "urma_173";
}
} // namespace diag
