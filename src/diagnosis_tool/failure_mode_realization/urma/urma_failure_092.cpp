#include "urma_failure_092.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure092> g_urma("urma_092");

bool UrmaFailure092::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_tp_attr") != std::string::npos &&
           message.find("Invalid tp_attr bytes.") != std::string::npos;
}

std::string UrmaFailure092::GetName() const
{
    return "TP、ATTR状态不满足要求导致获取TP、ATTR失败";
}

std::string UrmaFailure092::GetRootCauseDesc() const
{
    return "urma_cmd_get_tp_attr执行获取TP、ATTR时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure092::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure092::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure092::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_tp_attr，Invalid tp_attr bytes.。";
}

std::string UrmaFailure092::GetId() const
{
    return "urma_092";
}
} // namespace diag
