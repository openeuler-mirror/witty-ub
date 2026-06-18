#include "urma_failure_126.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure126> g_urma("urma_126");

bool UrmaFailure126::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_tp_list") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure126::GetName() const
{
    return "provider未提供modify_tp操作实现无效导致获取TP列表失败";
}

std::string UrmaFailure126::GetRootCauseDesc() const
{
    return "urma_get_tp_list用于获取TP列表，调用方传入的provider未提供modify_"
           "tp操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure126::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure126::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure126::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_tp_list，Invalid parameter.。";
}

std::string UrmaFailure126::GetId() const
{
    return "urma_126";
}
} // namespace diag
