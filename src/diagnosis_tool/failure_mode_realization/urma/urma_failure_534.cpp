#include "urma_failure_534.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure534> g_urma("urma_534");

bool UrmaFailure534::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jfr") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure534::GetName() const
{
    return "JFR、URMA context、dev_fd无效导致删除JFR失败";
}

std::string UrmaFailure534::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfr用于删除JFR，调用方传入的JFR、URMA "
           "context、dev_fd不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure534::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure534::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure534::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfr，Invalid parameter。";
}

std::string UrmaFailure534::GetId() const
{
    return "urma_534";
}
} // namespace diag
