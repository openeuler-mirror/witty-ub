#include "urma_failure_273.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure273> g_urma("urma_273");

bool UrmaFailure273::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_dmac") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure273::GetName() const
{
    return "provider未提供get_smac操作实现无效导致获取DMAC失败";
}

std::string UrmaFailure273::GetRootCauseDesc() const
{
    return "urma_get_dmac用于获取DMAC，调用方传入的provider未提供get_"
           "smac操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure273::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure273::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure273::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_dmac，Invalid parameter.。";
}

std::string UrmaFailure273::GetId() const
{
    return "urma_273";
}
} // namespace diag
