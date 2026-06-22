#include "urma_failure_414.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure414> g_urma("urma_414");

bool UrmaFailure414::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jfc_batch") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure414::GetName() const
{
    return "jfc_arr、bad_jfc无效导致删除JFC失败";
}

std::string UrmaFailure414::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfc_batch用于删除JFC，调用方传入的jfc_arr、bad_jfc不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure414::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure414::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure414::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfc_batch，Invalid parameter。";
}

std::string UrmaFailure414::GetId() const
{
    return "urma_414";
}
} // namespace diag
