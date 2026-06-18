#include "urma_failure_536.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure536> g_urma("urma_536");

bool UrmaFailure536::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jfr_batch") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure536::GetName() const
{
    return "jfr_arr、bad_jfr无效导致删除JFR失败";
}

std::string UrmaFailure536::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfr_batch用于删除JFR，调用方传入的jfr_arr、bad_jfr不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure536::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure536::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure536::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfr_batch，Invalid parameter.。";
}

std::string UrmaFailure536::GetId() const
{
    return "urma_536";
}
} // namespace diag
