#include "urma_1043_data_send_receive_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1043DataSendReceiveFailure> g_urma("urma_1043");

bool Urma1043DataSendReceiveFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {
        "urma_1044", "urma_1046", "urma_1050", "urma_1052", "urma_1055", "urma_1057", "urma_1060", "urma_1062",
        "urma_1065", "urma_1069", "urma_1071", "urma_1073", "urma_1078", "urma_1083", "urma_1086", "urma_1088",
        "urma_1090", "urma_1092", "urma_1094", "urma_1096", "urma_1098", "urma_1100", "urma_1103", "urma_1105",
        "urma_1108", "urma_1110", "urma_1112", "urma_1114", "urma_1117", "urma_1120"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1043DataSendReceiveFailure::GetName() const
{
    return "数据收发失败";
}

std::string Urma1043DataSendReceiveFailure::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause Urma1043DataSendReceiveFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1043DataSendReceiveFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1043DataSendReceiveFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1043DataSendReceiveFailure::GetId() const
{
    return "urma_1043";
}
} // namespace diag
