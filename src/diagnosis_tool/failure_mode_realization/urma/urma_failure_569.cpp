#include "urma_failure_569.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure569> g_urma("urma_569");

bool UrmaFailure569::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_deactive_jfs") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure569::GetName() const
{
    return "JFS无效导致去激活JFS失败";
}

std::string UrmaFailure569::GetRootCauseDesc() const
{
    return "urma_deactive_jfs用于去激活JFS，调用方传入的JFS不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure569::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure569::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure569::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jfs，Invalid parameter.。";
}

std::string UrmaFailure569::GetId() const
{
    return "urma_569";
}
} // namespace diag
