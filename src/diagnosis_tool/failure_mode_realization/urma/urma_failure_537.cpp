#include "urma_failure_537.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure537> g_urma("urma_537");

bool UrmaFailure537::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jfr_batch") != std::string::npos &&
           message.find("Invalid parameter, index:") != std::string::npos;
}

std::string UrmaFailure537::GetName() const
{
    return "jfr_arr、bad_jfr无效导致删除JFR失败";
}

std::string UrmaFailure537::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfr_batch用于删除JFR，调用方传入的jfr_arr、bad_jfr不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure537::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure537::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure537::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfr_batch，Invalid parameter, index:。";
}

std::string UrmaFailure537::GetId() const
{
    return "urma_537";
}
} // namespace diag
