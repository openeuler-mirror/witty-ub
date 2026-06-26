#include "urma_failure_188.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure188> g_urma("urma_188");

bool UrmaFailure188::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jfs") != std::string::npos &&
           message.find("Invalid parameter, trans_mode:") != std::string::npos &&
           message.find(", order_type:") != std::string::npos;
}

std::string UrmaFailure188::GetName() const
{
    return "JFS无效导致创建JFS失败";
}

std::string UrmaFailure188::GetRootCauseDesc() const
{
    return "urma_create_jfs用于创建JFS，调用方传入的JFS不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure188::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure188::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure188::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jfs，Invalid parameter, trans_mode:，, order_type:。";
}

std::string UrmaFailure188::GetId() const
{
    return "urma_188";
}
} // namespace diag
