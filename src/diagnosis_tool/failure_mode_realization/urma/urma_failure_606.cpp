#include "urma_failure_606.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure606> g_urma("urma_606");

bool UrmaFailure606::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_context") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure606::GetName() const
{
    return "URMA context、URMA设备、provider操作表、delete_context无效导致删除context失败";
}

std::string UrmaFailure606::GetRootCauseDesc() const
{
    return "urma_delete_context用于删除context，调用方传入的URMA "
           "context、URMA设备、provider操作表、delete_context不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure606::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure606::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string UrmaFailure606::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_context，Invalid parameter.。";
}

std::string UrmaFailure606::GetId() const
{
    return "urma_606";
}
} // namespace diag
